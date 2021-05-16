module.exports = {
  env: {
    node: true,
    es6: true,
    mocha: true,
  },
  extends: ['eslint:recommended'],
  parserOptions: {
    ecmaVersion: 2018,
  },
  rules: {
    'no-unused-vars': ['error', { varsIgnorePattern: "__", argsIgnorePattern: "__" }],
    'no-constant-condition': 'off'
  },
  overrides: [
    {
      files: ['*.test.js'],
      rules: {
        'no-unused-vars': 'off'
      }
    }
  ]
};
