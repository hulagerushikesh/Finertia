import * as React from "react"
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex w-fit items-center rounded-md border font-medium whitespace-nowrap transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
        // Verdict tones. Soft ground, strong text — the word carries the
        // colour, the pill never shouts.
        pencil: "border-transparent bg-pencil/10 text-pencil",
        gain: "border-transparent bg-gain/10 text-gain",
        loss: "border-transparent bg-loss/10 text-loss",
        warn: "border-transparent bg-warn/10 text-warn",
        faint: "border-transparent bg-muted text-muted-foreground",
      },
      size: {
        sm: "px-1.5 py-0 text-2xs",
        md: "px-2.5 py-0.5 text-xs",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
)

function Badge({
  className,
  variant,
  size,
  ...props
}) {
  return (<span className={cn(badgeVariants({ variant, size }), className)} {...props} />);
}

export { Badge, badgeVariants }
