import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

// ESLint flat config requires a default export.
export default tseslint.config(
  { ignores: ['dist', 'node_modules', 'src/api/generated'] },
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  react.configs.flat['recommended'],
  react.configs.flat['jsx-runtime'],
  reactHooks.configs.flat['recommended'],
  {
    languageOptions: {
      globals: { ...globals.browser },
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    settings: { react: { version: 'detect' } },
    rules: {
      'react/no-danger': 'error',
      'max-lines': ['error', { max: 500, skipBlankLines: false, skipComments: false }],
    },
  },
  { files: ['vite.config.ts'], languageOptions: { globals: globals.node } },
  { files: ['eslint.config.js'], extends: [tseslint.configs.disableTypeChecked] },
);
