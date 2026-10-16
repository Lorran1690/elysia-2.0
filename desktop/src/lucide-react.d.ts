declare module 'lucide-react' {
  import type { ComponentType, SVGProps } from 'react'

  type IconProps = SVGProps<SVGSVGElement> & {
    size?: number | string
    strokeWidth?: number | string
  }

  export const Activity: ComponentType<IconProps>
  export const Cpu: ComponentType<IconProps>
  export const Info: ComponentType<IconProps>
  export const Settings2: ComponentType<IconProps>
  export const Sparkles: ComponentType<IconProps>
}
