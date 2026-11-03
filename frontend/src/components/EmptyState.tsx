import { Link } from 'react-router';

// The shared state of an empty list: what is missing and, when there is one, where to go next.
export function EmptyState({
  message,
  action,
}: {
  message: string;
  action?: { to: string; label: string };
}): React.JSX.Element {
  return (
    <p>
      {message}
      {action !== undefined && (
        <>
          {' '}
          <Link to={action.to}>{action.label}</Link>
        </>
      )}
    </p>
  );
}
