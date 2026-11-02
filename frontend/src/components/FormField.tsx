import { useId } from 'react';

import styles from './ui.module.css';

const MULTILINE_ROWS = 5;

interface FormFieldProps {
  name: string;
  label: string;
  type?: 'text' | 'email' | 'password';
  multiline?: boolean;
  autoComplete?: string;
  defaultValue?: string;
  error?: string | undefined;
}

// A labelled input, or a textarea with `multiline`; its server message shows right under it.
// Uncontrolled: the form reads FormData.
export function FormField({
  name,
  label,
  type = 'text',
  multiline = false,
  autoComplete,
  defaultValue,
  error,
}: FormFieldProps): React.JSX.Element {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={styles.field}>
      <label htmlFor={id}>{label}</label>
      {multiline ? (
        <textarea
          id={id}
          name={name}
          rows={MULTILINE_ROWS}
          autoComplete={autoComplete}
          defaultValue={defaultValue}
          className={[styles.input, styles.textarea].join(' ')}
          aria-invalid={error === undefined ? undefined : true}
          aria-describedby={error === undefined ? undefined : errorId}
        />
      ) : (
        <input
          id={id}
          name={name}
          type={type}
          autoComplete={autoComplete}
          defaultValue={defaultValue}
          className={styles.input}
          aria-invalid={error === undefined ? undefined : true}
          aria-describedby={error === undefined ? undefined : errorId}
        />
      )}
      {error !== undefined && (
        <p id={errorId} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
}
