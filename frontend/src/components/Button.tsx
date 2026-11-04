import styles from './ui.module.css';

export type ButtonKind = 'primary' | 'secondary' | 'danger';

const KIND_CLASS: Record<ButtonKind, string | undefined> = {
  primary: styles.primary,
  secondary: undefined,
  danger: styles.dangerButton,
};

type ButtonProps = Omit<React.ComponentPropsWithoutRef<'button'>, 'type'> & {
  kind?: ButtonKind;
  type?: 'button' | 'submit' | 'reset';
};

// The one button of the SPA: a kind picks the look, `type` defaults to "button".
export function Button({
  kind = 'secondary',
  type = 'button',
  className,
  ...rest
}: ButtonProps): React.JSX.Element {
  const classes = [styles.button, KIND_CLASS[kind], className].filter(Boolean).join(' ');
  return <button {...rest} type={type} className={classes} data-kind={kind} />;
}
