import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PlacementBadge } from './PlacementBadge';

// Task 2.2 of 1-8-visual-system: the placement reason is a badge with the exact label and a kind.

describe('PlacementBadge', () => {
  it('shows «Вручную» with the kind manual', () => {
    render(
      <PlacementBadge placement={{ kind: 'manual', engine_version: null, similarity: null }} />,
    );

    expect(screen.getByText('Вручную')).toHaveAttribute('data-kind', 'manual');
  });

  it('shows «Правило · адрес …» with the kind rule', () => {
    render(
      <PlacementBadge
        placement={{
          kind: 'rule',
          engine_version: null,
          similarity: null,
          rule: { condition: 'address', value: 's.petrov@stroymaster.example' },
        }}
      />,
    );

    expect(screen.getByText('Правило · адрес s.petrov@stroymaster.example')).toHaveAttribute(
      'data-kind',
      'rule',
    );
  });

  it('shows «Движок text-1 · сходство 43%» with the kind engine', () => {
    render(
      <PlacementBadge
        placement={{ kind: 'engine', engine_version: 'text-1', similarity: 0.4271 }}
      />,
    );

    expect(screen.getByText('Движок text-1 · сходство 43%')).toHaveAttribute('data-kind', 'engine');
  });
});
