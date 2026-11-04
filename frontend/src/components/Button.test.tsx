import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Button } from './Button';

// Task 2.2 of 1-8-visual-system: the kinds of a button.

describe('Button', () => {
  it('renders a <button> named by its children with type="button" by default', () => {
    render(<Button>Сохранить</Button>);

    const button = screen.getByRole('button', { name: 'Сохранить' });
    expect(button.tagName).toBe('BUTTON');
    expect(button).toHaveAttribute('type', 'button');
  });

  it('is secondary by default', () => {
    render(<Button>Сохранить</Button>);

    expect(screen.getByRole('button', { name: 'Сохранить' })).toHaveAttribute(
      'data-kind',
      'secondary',
    );
  });

  it.each(['primary', 'danger'] as const)('exposes the kind %s as data-kind', (kind) => {
    render(<Button kind={kind}>Сохранить</Button>);

    expect(screen.getByRole('button', { name: 'Сохранить' })).toHaveAttribute('data-kind', kind);
  });

  it('passes native button props through', () => {
    render(
      <Button type="submit" disabled>
        Отправить
      </Button>,
    );

    const button = screen.getByRole('button', { name: 'Отправить' });
    expect(button).toHaveAttribute('type', 'submit');
    expect(button).toBeDisabled();
  });
});
