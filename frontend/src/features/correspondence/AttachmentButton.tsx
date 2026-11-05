import { useMutation } from '@tanstack/react-query';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { unwrap } from '../../api/request';
import { Button } from '../../components/Button';
import { ErrorAlert } from '../../components/ErrorAlert';
import styles from './ChainPage.module.css';
import { formatAttachment } from './format';

type AttachmentView = components['schemas']['AttachmentView'];

// Saves the blob under the name through a temporary object URL; the browser never opens it.
function saveBlob(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// One attachment as a button that downloads it; a refusal is shown under this attachment only.
export function AttachmentButton({
  emailId,
  attachment,
}: {
  emailId: string;
  attachment: AttachmentView;
}): React.JSX.Element {
  const download = useMutation({
    mutationFn: () =>
      unwrap(
        apiClient.GET('/api/v1/emails/{email_id}/attachments/{index}', {
          params: { path: { email_id: emailId, index: attachment.index } },
          parseAs: 'blob',
        }),
      ),
    onSuccess: (blob) => {
      saveBlob(blob, attachment.name);
    },
  });
  return (
    <li className={styles.attachment}>
      <Button
        disabled={download.isPending}
        onClick={() => {
          download.mutate();
        }}
      >
        {formatAttachment(attachment)}
      </Button>
      <ErrorAlert error={download.error} />
    </li>
  );
}
