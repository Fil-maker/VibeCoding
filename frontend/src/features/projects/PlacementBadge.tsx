import { placementLabel } from './format';
import styles from './PlacementBadge.module.css';

// The reason a chain sits where it does, as a badge: the text carries the kind, the color repeats it.
export function PlacementBadge({
  placement,
}: {
  placement: Parameters<typeof placementLabel>[0];
}): React.JSX.Element {
  return (
    <span className={[styles.badge, styles[placement.kind]].join(' ')} data-kind={placement.kind}>
      {placementLabel(placement)}
    </span>
  );
}
