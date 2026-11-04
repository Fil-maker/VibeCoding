import { useId } from 'react';

import type { MailService } from './mailServices';

// «Как подключить <service>»: a region named by its title, with the steps and the official help
// link; nothing for demo and other.
export function ServiceSteps({ service }: { service: MailService }): React.JSX.Element | null {
  const titleId = useId();
  if (service.howToTitle === null) {
    return null;
  }
  return (
    <section aria-labelledby={titleId}>
      <h3 id={titleId}>{service.howToTitle}</h3>
      <ol>
        {service.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      {service.help !== null && (
        <a href={service.help.url} target="_blank" rel="noopener noreferrer">
          {service.help.label}
        </a>
      )}
    </section>
  );
}
