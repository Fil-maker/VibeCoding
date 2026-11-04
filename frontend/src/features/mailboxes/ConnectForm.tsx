import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useId, useState } from 'react';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { fieldErrors, unwrap } from '../../api/request';
import { Button } from '../../components/Button';
import { ErrorAlert } from '../../components/ErrorAlert';
import styles from '../../components/ui.module.css';
import { MAILBOXES_KEY } from './mailboxesKey';
import {
  MAIL_SERVICES,
  domainOfAddress,
  serviceById,
  serviceForAddress,
  type MailServiceId,
} from './mailServices';
import { ServiceSteps } from './ServiceSteps';

const ADDRESS_MESSAGE = 'Укажите адрес почты';
const SERVER_MESSAGE = 'Укажите сервер IMAP';
const PASSWORD_MESSAGE = 'Укажите пароль приложения';
const PORT_MESSAGE = 'Порт должен быть от 1 до 65535';
const PORT_MIN = 1;
const PORT_MAX = 65535;
const OTHER_HINT =
  'Этот почтовый сервис нам незнаком. Адрес сервера IMAP и порт есть в справке вашей почты или у администратора домена.';

interface FormState {
  address: string;
  password: string;
  serviceId: MailServiceId;
  // The domain at the moment of a hand pick; null while the service follows the address.
  pickedDomain: string | null;
  server: string;
  port: string;
  login: string;
  serverEdited: boolean;
  portEdited: boolean;
  loginEdited: boolean;
  // The user's own open/close of «Настройки сервера»; null while it follows the service.
  settingsByHand: boolean | null;
}

const INITIAL_STATE: FormState = {
  address: '',
  password: '',
  serviceId: 'other',
  pickedDomain: null,
  server: '',
  port: String(serviceById('other').port),
  login: '',
  serverEdited: false,
  portEdited: false,
  loginEdited: false,
  settingsByHand: null,
};

// Typing the address picks the service and fills the fields the user has not edited by hand.
function withAddress(state: FormState, address: string): FormState {
  const domain = domainOfAddress(address);
  const keepPick = state.pickedDomain !== null && state.pickedDomain === domain;
  const service = keepPick ? serviceById(state.serviceId) : serviceForAddress(address);
  return {
    ...state,
    address,
    serviceId: service.id,
    pickedDomain: keepPick ? state.pickedDomain : null,
    server: state.serverEdited ? state.server : service.server,
    port: state.portEdited ? state.port : String(service.port),
    login: state.loginEdited ? state.login : address.trim(),
  };
}

// A hand pick is a deliberate choice: it refills the server and the port, never the login.
function withPickedService(state: FormState, id: MailServiceId): FormState {
  const service = serviceById(id);
  return {
    ...state,
    serviceId: id,
    pickedDomain: domainOfAddress(state.address),
    server: service.server,
    port: String(service.port),
    serverEdited: false,
    portEdited: false,
  };
}

interface TextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: 'text' | 'password';
  autoComplete?: string;
  error?: string | undefined;
}

// A labelled input; `error` is set only while the field has a message, which sets aria-invalid.
function TextField({
  label,
  value,
  onChange,
  type = 'text',
  autoComplete,
  error,
}: TextFieldProps): React.JSX.Element {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={styles.field}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type={type}
        value={value}
        autoComplete={autoComplete}
        className={styles.input}
        aria-invalid={error === undefined ? undefined : true}
        aria-describedby={error === undefined ? undefined : errorId}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      />
      {error !== undefined && (
        <p id={errorId} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
}

// With an empty address the request is not sent; the other fields get the server's exact texts.
function emptyAddressErrors(state: FormState): ReadonlyMap<string, string> {
  const port = Number(state.port);
  const errors = new Map<string, string>([['address', ADDRESS_MESSAGE]]);
  if (state.server.trim() === '') {
    errors.set('server', SERVER_MESSAGE);
  }
  if (!Number.isInteger(port) || port < PORT_MIN || port > PORT_MAX) {
    errors.set('port', PORT_MESSAGE);
  }
  if (state.password === '') {
    errors.set('password', PASSWORD_MESSAGE);
  }
  return errors;
}

function hasSettingsError(errors: ReadonlyMap<string, string>, loginEdited: boolean): boolean {
  return errors.has('server') || errors.has('port') || (loginEdited && errors.has('login'));
}

// «Подключить ящик». The address comes first and picks the service; the server and the port follow
// the service, and the login follows the address. A value the user typed by hand is kept, except that
// a service picked by hand refills the server and the port.
export function ConnectForm(): React.JSX.Element {
  const queryClient = useQueryClient();
  const serviceFieldId = useId();
  const [state, setState] = useState<FormState>(INITIAL_STATE);
  const [clientErrors, setClientErrors] = useState<ReadonlyMap<string, string> | null>(null);
  const connect = useMutation({
    mutationFn: (body: components['schemas']['MailboxConnect']) =>
      unwrap(apiClient.POST('/api/v1/mailboxes', { body })),
    onSuccess: async () => {
      setState(INITIAL_STATE);
      await queryClient.invalidateQueries({ queryKey: MAILBOXES_KEY });
    },
    onError: (error) => {
      if (hasSettingsError(fieldErrors(error), state.loginEdited)) {
        setState((current) => ({ ...current, settingsByHand: true }));
      }
    },
  });
  const errors = clientErrors ?? fieldErrors(connect.error);
  const service = serviceById(state.serviceId);
  const addressError =
    errors.get('address') ??
    (errors.has('login') && !state.loginEdited ? ADDRESS_MESSAGE : undefined);
  const showHint =
    service.id === 'other' &&
    (state.pickedDomain !== null || domainOfAddress(state.address) !== '');
  const settingsOpen = state.settingsByHand ?? showHint;

  return (
    <>
      <h2 className={styles.subheading}>Подключить ящик</h2>
      <form
        className={styles.form}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          connect.reset();
          if (state.address.trim() === '') {
            const found = emptyAddressErrors(state);
            setClientErrors(found);
            if (found.has('server') || found.has('port')) {
              setState((current) => ({ ...current, settingsByHand: true }));
            }
            return;
          }
          setClientErrors(null);
          connect.mutate({
            server: state.server,
            port: Number(state.port),
            login: state.login,
            password: state.password,
          });
        }}
      >
        <ErrorAlert error={errors.size > 0 ? null : connect.error} />
        <TextField
          label="Адрес почты"
          value={state.address}
          autoComplete="email"
          error={addressError}
          onChange={(value) => {
            setState((current) => withAddress(current, value));
          }}
        />
        <div className={styles.field}>
          <label htmlFor={serviceFieldId}>Почтовый сервис</label>
          <select
            id={serviceFieldId}
            className={styles.input}
            value={state.serviceId}
            onChange={(event) => {
              const id = MAIL_SERVICES.find((item) => item.id === event.target.value)?.id;
              if (id !== undefined) {
                setState((current) => withPickedService(current, id));
              }
            }}
          >
            {MAIL_SERVICES.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
        {showHint && <p>{OTHER_HINT}</p>}
        <ServiceSteps service={service} />
        <details
          open={settingsOpen}
          onToggle={(event) => {
            const open = event.currentTarget.open;
            // React sets the attribute itself; only a differing state is the user's own toggle.
            if (open !== settingsOpen) {
              setState((current) => ({ ...current, settingsByHand: open }));
            }
          }}
        >
          <summary>Настройки сервера</summary>
          <TextField
            label="Сервер IMAP"
            value={state.server}
            error={errors.get('server')}
            onChange={(value) => {
              setState((current) => ({ ...current, server: value, serverEdited: true }));
            }}
          />
          <TextField
            label="Порт"
            value={state.port}
            error={errors.get('port')}
            onChange={(value) => {
              setState((current) => ({ ...current, port: value, portEdited: true }));
            }}
          />
          <TextField
            label="Логин"
            value={state.login}
            autoComplete="username"
            error={state.loginEdited ? errors.get('login') : undefined}
            onChange={(value) => {
              setState((current) => ({ ...current, login: value, loginEdited: true }));
            }}
          />
        </details>
        <TextField
          label="Пароль приложения"
          type="password"
          value={state.password}
          autoComplete="off"
          error={errors.get('password')}
          onChange={(value) => {
            setState((current) => ({ ...current, password: value }));
          }}
        />
        <Button type="submit" kind="primary" disabled={connect.isPending}>
          Подключить
        </Button>
      </form>
    </>
  );
}
