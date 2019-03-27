module.exports = {
  parser: 'babel-eslint',
  env: {
    browser: true,
    commonjs: true,
    es6: true,
    amd: true,
  },
  extends: ['airbnb', 'plugin:react/recommended', 'plugin:prettier/recommended'],
  parserOptions: {
    ecmaVersion: 8,
    ecmaFeatures: {
      ecmaVersion: 2019,
      jsx: true,
    },
    sourceType: 'module',
  },
  plugins: ['react-hooks'],
  settings: {
    react: {
      pragma: 'React',
      version: '16.8.5',
    },
  },
  rules: {
    indent: ['error', 2, { SwitchCase: 1 }],
    'keyword-spacing': 'error',
    'linebreak-style': ['error', 'unix'],
    'no-undef': 0,
    'no-unsued-vars': 0,
    'prettier/prettier': 'error',
    quotes: ['error', 'single'],
    'react/prop-types': 2,
    'react/jsx-filename-extension': 0,
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    semi: ['error', 'always'],
    'space-before-blocks': 'error',
  },
};
