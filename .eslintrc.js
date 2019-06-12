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
    'keyword-spacing': 'error',
    'import/named': 0,
    'import/prefer-default-export': 0,
    indent: ['error', 2, { SwitchCase: 1 }],
    'linebreak-style': ['error', 'unix'],
    'no-plusplus': 0,
    'no-undef': 0,
    'no-unsued-vars': 0,
    'prettier/prettier': 'error',
    quotes: ['error', 'single'],
    'react/prop-types': 2,
    'react/require-default-props': 0,
    'react/jsx-filename-extension': 0,
    'react-hooks/rules-of-hooks': 'error',
    semi: ['error', 'always'],
    'space-before-blocks': 'error',
  },
};
