import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Reveal } from "./reveal";

export function SectionHeading({
  eyebrow,
  title,
  description,
  className,
  as: Heading = "h2",
}: {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  className?: string;
  /** h1 when the heading opens its own page, h2 inside the home page. */
  as?: "h1" | "h2";
}) {
  return (
    <div className={cn("flex flex-col items-start gap-6", className)}>
      <Reveal className="max-w-3xl">
        <p className="eyebrow mb-4">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-claw-400" />
          {eyebrow}
        </p>
        <Heading className="text-balance text-[2rem] font-semibold leading-[1.08] tracking-tighter sm:text-4xl md:text-5xl">
          <span className="gradient-text">{title}</span>
        </Heading>
        {description && (
          <p className="mt-5 text-pretty text-base leading-relaxed text-fog-muted sm:text-lg">{description}</p>
        )}
      </Reveal>
    </div>
  );
}
