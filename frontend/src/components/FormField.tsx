import { useId } from 'react';

import styles from './ui.module.css';

interface FormFieldProps {
  name: string;
  label: string;
  type?: 'text' | 'email' | 'password';
  autoComplete?: string;
  defaultValue?: string;
  error?: string | undefined;
}

// A labelled input; its server message shows right under it. Uncontrolled: the form reads FormData.
export function FormField({
  name,
  label,
  type = 'text',
  autoComplete,
  defaultValue,
  error,
}: FormFieldProps): React.JSX.Element {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={styles.field}>
      <label htmlFor={id}>{label}</label>
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
      {error !== undefined && (
        <p id={errorId} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
}
