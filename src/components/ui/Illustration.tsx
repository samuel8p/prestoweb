export type IllustrationName = 'empty' | 'error' | 'success'

export interface IllustrationProps {
  name: IllustrationName
  className?: string
}

/**
 * Ilustraciones geométricas propias para los estados vacíos y de error.
 *
 * SVG dibujado a mano con la paleta del producto: sin recursos externos.
 */
export function Illustration({ name, className = '' }: IllustrationProps) {
  if (name === 'error') {
    return (
      <svg
        width="120"
        height="96"
        viewBox="0 0 120 96"
        fill="none"
        aria-hidden="true"
        focusable="false"
        className={className}
      >
        <rect x="18" y="20" width="84" height="60" rx="10" fill="#FCECE8" />
        <path d="M60 34 78 68H42L60 34Z" fill="#F6D9D1" />
        <path d="M60 34 78 68H42L60 34Z" stroke="#B53624" strokeWidth="2" strokeLinejoin="round" />
        <path d="M60 46v10" stroke="#B53624" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="60" cy="62" r="1.8" fill="#B53624" />
        <path d="M8 84h104" stroke="#E7E0D4" strokeWidth="2" strokeLinecap="round" />
      </svg>
    )
  }

  if (name === 'success') {
    return (
      <svg
        width="120"
        height="96"
        viewBox="0 0 120 96"
        fill="none"
        aria-hidden="true"
        focusable="false"
        className={className}
      >
        <rect x="18" y="20" width="84" height="60" rx="10" fill="#E7F5EC" />
        <circle cx="60" cy="50" r="16" fill="#CFEBD9" />
        <path
          d="M52 50l6 6 11-12"
          stroke="#117635"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M8 84h104" stroke="#E7E0D4" strokeWidth="2" strokeLinecap="round" />
      </svg>
    )
  }

  return (
    <svg
      width="120"
      height="96"
      viewBox="0 0 120 96"
      fill="none"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <rect x="18" y="20" width="84" height="60" rx="10" fill="#F6F2EA" />
      <path d="M30 38h34" stroke="#E7E0D4" strokeWidth="4" strokeLinecap="round" />
      <path d="M30 50h52" stroke="#E7E0D4" strokeWidth="4" strokeLinecap="round" />
      <path d="M30 62h22" stroke="#E7E0D4" strokeWidth="4" strokeLinecap="round" />
      <circle cx="84" cy="58" r="18" fill="#E4F0F1" />
      <circle cx="84" cy="58" r="18" stroke="#0E7C86" strokeWidth="2" />
      <path d="M78 58h12" stroke="#0E7C86" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M8 84h104" stroke="#E7E0D4" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
