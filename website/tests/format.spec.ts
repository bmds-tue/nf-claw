import { expect, test } from "@playwright/test";
import { groupByMonth, humanizeCron } from "../src/lib/format";

// The activity section words each workflow's schedule; a schedule it cannot word is shown as written.
test("cron schedules are worded only when the wording is right", () => {
  expect(humanizeCron("0 6 * * *")).toBe("Daily at 06:00 UTC");
  expect(humanizeCron("17 4 * * 1")).toBe("Weekly · Mon 04:17 UTC");
  expect(humanizeCron("0 6 * * 3")).toBe("Weekly · Wed 06:00 UTC");
  expect(humanizeCron("0 6 * * 7")).toBe("Weekly · Sun 06:00 UTC");
  expect(humanizeCron("0 6 1 * *")).toBe("Scheduled · 06:00 UTC");
  expect(humanizeCron("15 * * * *")).toBe("Hourly at :15");
  expect(humanizeCron("* * * * *")).toBe("Every minute");
  for (const raw of ["*/30 * * * *", "0 6 * * 1-5", "0 6,18 * * *", "0 */6 * * *", "* 6 * * *"]) {
    expect(humanizeCron(raw), raw).toBe(raw);
  }
  expect(humanizeCron(null)).toBeNull();
});

// A git date keeps its committer's offset; months are grouped in UTC, as they are labelled.
test("timeline months follow the UTC month their label names", () => {
  const groups = groupByMonth([
    { date: "2026-04-02T10:00:00+00:00" },
    { date: "2026-03-31T23:30:00-05:00" },
    { date: "2026-03-15T12:00:00+02:00" },
    { date: null },
  ]);
  expect(groups.map((g) => [g.key, g.label, g.items.length])).toEqual([
    ["2026-04", "April 2026", 2],
    ["2026-03", "March 2026", 1],
    ["undated", "Undated", 1],
  ]);
});
