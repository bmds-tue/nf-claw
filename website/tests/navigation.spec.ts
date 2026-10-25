import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ page }) => {
  const problems: string[] = [];
  page.on("pageerror", (error) => problems.push(error.message));
  page.on("response", (response) => {
    if (response.url().startsWith("http://127.0.0.1:4177/") && response.status() >= 400) {
      problems.push(`${response.status()} ${response.url()}`);
    }
  });
  page.on("requestfailed", (request) => {
    if (request.url().startsWith("http://127.0.0.1:4177/") && request.failure()?.errorText !== "net::ERR_ABORTED") {
      problems.push(`failed ${request.url()}`);
    }
  });
  await page.goto("./");
  (page as unknown as { testProblems: string[] }).testProblems = problems;
});

test.afterEach(async ({ page }) => {
  expect((page as unknown as { testProblems: string[] }).testProblems).toEqual([]);
});

test("search opens, traps focus, closes, restores focus and navigates by keyboard", async ({ page }) => {
  const trigger = page.getByRole("navigation", { name: "Main", exact: true }).getByRole("button", { name: /^Search/ });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Search nf-claw" });
  const input = dialog.getByRole("combobox");
  await expect(input).toBeFocused();
  await input.press("Tab");
  await expect(dialog.getByRole("button", { name: "Close search" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(input).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
  await page.keyboard.press("Control+k");
  await input.fill("rnaseq");
  await expect(input).toHaveAttribute("aria-activedescendant", "palette-p-rnaseq");
  await input.press("ArrowDown");
  await input.press("ArrowUp");
  await input.press("Enter");
  await expect(page).toHaveURL(/\/nf-claw\/pipelines\/rnaseq\/$/);
  await expect(dialog).toBeHidden();
  await page.goBack();
  await trigger.click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Close search" }).click();
  await expect(dialog).toBeHidden();
});

test("full-text remedies link to their documented section and render a useful snippet", async ({ page }) => {
  await page.keyboard.press("Control+k");
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("combobox").fill("Network is unreachable");
  const remedy = dialog.getByRole("option").filter({ hasText: /Network is unreachable/i }).first();
  await expect(remedy).toBeVisible();
  await remedy.click();
  await expect(page).toHaveURL(/\/nf-claw\/docs\/[^/]+\/#.+/);
  const fragment = decodeURIComponent(new URL(page.url()).hash.slice(1));
  await expect(page.locator(`[id=${JSON.stringify(fragment)}]`)).toBeVisible();
  expect(await page.locator("main").innerText()).toContain("Network is unreachable");
});

test("documentation search loads lazily and treats query markup as text", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => { if (request.url().endsWith("/search/docs.json")) requests.push(request.url()); });
  await page.reload();
  expect(requests).toEqual([]);
  await page.keyboard.press("Control+k");
  await expect.poll(() => requests.length).toBe(1);
  const dialog = page.getByRole("dialog");
  const input = dialog.getByRole("combobox");
  let alert = false;
  page.on("dialog", async (event) => { alert = true; await event.dismiss(); });
  await input.fill('<img src=x onerror="alert(1)">');
  await expect(dialog.getByText(/No results for/)).toBeVisible();
  await expect(dialog.locator("img")).toHaveCount(0);
  expect(alert).toBe(false);
  await input.press("Escape");
  await page.keyboard.press("Control+k");
  await expect(dialog).toBeVisible();
  expect(requests).toHaveLength(1);
});

test("URL filters survive reload, back and forward", async ({ page }) => {
  await page.goto("pipelines/?q=rnaseq");
  const search = page.getByRole("textbox", { name: "Search pipelines" });
  await expect(search).toHaveValue("rnaseq");
  await expect(page.locator('main a[href$="/pipelines/rnaseq/"] article')).toHaveCount(1);
  const matches = await page.locator("main article").count();
  await page.getByRole("button", { name: /^Epigenomics/ }).click();
  await expect(page).toHaveURL(/domain=Epigenomics/);
  await page.goBack();
  await expect(search).toHaveValue("rnaseq");
  await expect(page.locator("main article")).toHaveCount(matches);
  await page.goForward();
  await expect(page.getByRole("button", { name: /^Epigenomics/ })).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(search).toHaveValue("rnaseq");
  await expect(page.getByRole("button", { name: /^Epigenomics/ })).toHaveAttribute("aria-pressed", "true");
});

test("pipeline parameter search, documentation links and anchors work under the base path", async ({ page }) => {
  await page.goto("pipelines/rnaseq/?q=aligner#parameters");
  const search = page.getByRole("textbox", { name: "Search parameters" });
  await expect(search).toHaveValue("aligner");
  await expect(page.getByRole("button", { name: /--aligner/ }).first()).toBeVisible();
  await search.fill("not_a_real_parameter_12345");
  await expect(page.getByText(/No parameters/)).toBeVisible();
  await page.goto("docs/agents/");
  const guide = page.locator("main").getByRole("link", { name: "Replay guide", exact: true }).first();
  await expect(guide).toHaveAttribute("href", /\/nf-claw\/docs\/replay-guide\//);
  await guide.click();
  await expect(page).toHaveURL(/\/nf-claw\/docs\/replay-guide\/$/);
  await expect(page.locator("#replaying-a-run")).toBeVisible();
});

test("the home parameter index still finds a pipeline and carries its query into the explorer", async ({ page }) => {
  await page.getByRole("textbox", { name: "Search skills and parameters" }).fill("strandedness");
  await expect(page.getByText(/matching parameter/).first()).toBeVisible();
  const expand = page.getByRole("button", { name: /Show all.*skills/ });
  if (await expand.isVisible()) await expand.click();
  await page.locator('[data-skill="rnaseq"]').click();
  const explorer = page.getByRole("link", { name: "Full parameter explorer", exact: true });
  await expect(explorer).toHaveAttribute("href", /pipelines\/rnaseq\/\?q=strandedness#parameters/);
  await explorer.click();
  await expect(page.getByRole("textbox", { name: "Search parameters" })).toHaveValue("strandedness");
});

test("navigation and the search dialog expose accessible controls", async ({ page }) => {
  const navigation = await new AxeBuilder({ page }).include("header").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(navigation.violations).toEqual([]);
  await page.keyboard.press("Control+k");
  const dialog = await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(dialog.violations).toEqual([]);
});

test("mobile navigation closes on Escape and returns focus to its toggle", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "mobile viewport behavior");
  const toggle = page.locator('button[aria-controls="mobile-menu"]');
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Escape");
  await expect(toggle).toBeFocused();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await page.locator("#mobile-menu").getByRole("link", { name: "Docs", exact: true }).click();
  await expect(page).toHaveURL(/\/nf-claw\/docs\/$/);
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
});
