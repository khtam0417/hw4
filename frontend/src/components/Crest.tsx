/**
 * The Campus Customs shield monogram: the logo in the header and footer, the chat assistant's avatar
 * and the favicon. It is the shop's own mark, not a Yale emblem. Add "crest-light" on dark backgrounds.
 */
export default function Crest({ className = '' }: { className?: string }) {
  return (
    <svg className={`crest ${className}`.trim()} viewBox="0 0 48 56" aria-hidden="true" focusable="false">
      <path className="crest-shield" d="M24 1.5 45.5 8v19.2C45.5 41.4 36 50.6 24 54.5 12 50.6 2.5 41.4 2.5 27.2V8Z" />
      <path className="crest-rule" d="M24 6 41.2 11.2v16c0 11.6-7.6 19.4-17.2 23-9.6-3.6-17.2-11.4-17.2-23v-16Z" />
      <text className="crest-text" x="24" y="34.5" textAnchor="middle">
        CC
      </text>
    </svg>
  )
}
