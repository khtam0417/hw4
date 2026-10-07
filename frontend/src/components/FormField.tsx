import type { InputHTMLAttributes } from 'react'

type FormFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'onChange'> & {
  label: string
  name: string
  error?: string
  hint?: string
  onValueChange: (value: string) => void
}

/** A labelled input that shows its own error (or a hint) underneath. */
export default function FormField({ label, name, error, hint, onValueChange, ...input }: FormFieldProps) {
  const noteId = `${name}-note`
  const note = error ?? hint
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      <input
        id={name}
        name={name}
        {...input}
        onChange={(event) => onValueChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={note ? noteId : undefined}
      />
      {note && (
        <p id={noteId} className={error ? 'field-error' : 'field-hint'}>
          {note}
        </p>
      )}
    </div>
  )
}
