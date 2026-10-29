import type { Metadata, Viewport } from "next";
import "./globals.css";
import { BackgroundFX } from "@/components/ui/background-fx";
import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { CommandPalette, type PaletteData } from "@/components/layout/command-palette";
import { BackToTop } from "@/components/layout/back-to-top";
import { getRepoMeta, getPipelines, getDocs } from "@/lib/data";
import { categorize } from "@/lib/derive";
import { plainText } from "@/components/ui/inline-markdown";
import { BASE_PATH, OG_IMAGE, SITE_ORIGIN } from "@/lib/site";

const meta = getRepoMeta();

export const metadata: Metadata = {
  metadataBase: new URL(SITE_ORIGIN),
  title: {
    default: "nf-claw — nf-core pipelines for AI agents",
    template: "%s · nf-claw",
  },
  description: plainText(meta.tagline),
  applicationName: "nf-claw",
  keywords: ["nf-core", "nextflow", "bioinformatics", "pipelines", "AI agents", "nf-claw"],
  twitter: { card: "summary", title: "nf-claw", description: plainText(meta.tagline) },
  openGraph: {
    siteName: "nf-claw",
    title: "nf-claw",
    description: plainText(meta.tagline),
    type: "website",
    images: [OG_IMAGE],
  },
  // Right-sized renditions of the 3000 px source logo (docs/images/nf-claw-logo.png, ~3 MB).
  icons: {
    icon: [
      { url: `${BASE_PATH}/brand/logo-64.png`, sizes: "64x64", type: "image/png" },
      { url: `${BASE_PATH}/brand/logo-192.png`, sizes: "192x192", type: "image/png" },
    ],
    apple: `${BASE_PATH}/brand/apple-touch-icon.png`,
  },
};

export const viewport: Viewport = {
  themeColor: "#07080a",
  width: "device-width",
  initialScale: 1,
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pipelines = getPipelines();
  const palette: PaletteData = {
    pipelines: pipelines.map((p) => ({
      name: p.name,
      version: p.version,
      category: categorize(p),
      description: p.description,
    })),
    docs: getDocs().map((d) => ({ slug: d.slug, title: d.title, source: d.source })),
  };

  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        {/* Entrance animations render their first frame (opacity 0) into the static HTML, and only
            a script lifts it: without one, show that content as it ends up. */}
        <noscript
          dangerouslySetInnerHTML={{
            __html: '<style>[style*="opacity:0;"],[style$="opacity:0"]{opacity:1!important}</style>',
          }}
        />
        <BackgroundFX />
        <Nav repo={meta.remote} />
        <main id="main" className="relative" tabIndex={-1}>
          {children}
        </main>
        <Footer repo={meta.remote} pipelines={pipelines} />
        <CommandPalette data={palette} />
        <BackToTop />
      </body>
    </html>
  );
}
