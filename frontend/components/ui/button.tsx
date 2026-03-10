import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-gradient-to-r from-primary to-primary/85 text-primary-foreground shadow-sm hover:shadow-md hover:-translate-y-0.5 active:translate-y-0",
        destructive:
          "bg-gradient-to-r from-destructive to-destructive/85 text-destructive-foreground shadow-sm hover:shadow-md hover:-translate-y-0.5",
        outline:
          "border-2 border-border bg-background hover:bg-gradient-to-r hover:from-primary/5 hover:to-accent/5 hover:border-primary hover:text-primary transition-all",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 shadow-sm hover:shadow",
        ghost: "hover:bg-accent/10 hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline hover:text-primary/80",
        accent:
          "bg-gradient-to-r from-accent to-accent/85 text-foreground shadow-sm hover:shadow-md hover:-translate-y-0.5 active:translate-y-0",
        "accent-outline":
          "border-2 border-accent bg-background hover:bg-accent/10 hover:text-accent-foreground transition-all",
        success:
          "bg-gradient-to-r from-green-600 to-green-500 text-white shadow-sm hover:shadow-md hover:-translate-y-0.5",
        warning:
          "bg-gradient-to-r from-amber-600 to-amber-500 text-white shadow-sm hover:shadow-md hover:-translate-y-0.5",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-12 rounded-lg px-8 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }