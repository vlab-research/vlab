module.exports = {
  devServer: {
    https: true,
    key: './tmp/certs/key.pem',
    cert: './tmp/certs/cert.pem',
  },
  style: {
    postcss: {
      plugins: [
        require('tailwindcss'),
        require('autoprefixer'),
      ],
    },
  },
}
