import type { ReactNode, SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

/** Shared frame for the small stroke icons used across the site. */
function Icon({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  )
}

export const SearchIcon = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </Icon>
)

export const ChatIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1.1-4.3A8 8 0 1 1 21 12Z" />
  </Icon>
)

export const CloseIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M18 6 6 18M6 6l12 12" />
  </Icon>
)

export const MenuIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Icon>
)

export const UserIcon = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21a8 8 0 0 1 16 0" />
  </Icon>
)

export const ShieldIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 3 19 6v6c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6l7-3Z" />
    <path d="m9 12 2 2 4-4" />
  </Icon>
)

export const ShirtIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 3 4 5.5 2 10l3 1.5V21h14v-9.5l3-1.5-2-4.5L15 3a3 3 0 0 1-6 0Z" />
  </Icon>
)

export const PinIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 21s-7-6.2-7-11a7 7 0 1 1 14 0c0 4.8-7 11-7 11Z" />
    <circle cx="12" cy="10" r="2.5" />
  </Icon>
)

export const MailIcon = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="m3 7 9 6 9-6" />
  </Icon>
)

// The arrows nudge in the direction they point when their button or link is hovered (index.css).
export const ArrowRightIcon = (props: IconProps) => (
  <Icon className="icon-arrow-right" {...props}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Icon>
)

export const ArrowLeftIcon = (props: IconProps) => (
  <Icon className="icon-arrow-left" {...props}>
    <path d="M19 12H5M11 6l-6 6 6 6" />
  </Icon>
)

export const SendIcon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M22 2 11 13" />
    <path d="M22 2 15 22l-4-9-9-4 20-7Z" />
  </Icon>
)
