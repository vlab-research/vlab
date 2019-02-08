const {Storage} = require('@google-cloud/storage')

async function get(key) {
  const storage = new Storage()

  const exists = await storage
        .bucket(process.env.DB_BUCKET)
        .file(key)
        .exists()

  if (!exists[0]) return

  const res = await storage
        .bucket(process.env.DB_BUCKET)
        .file(key)
        .download()

  return res
    .toString()
    .split('\n')
    .filter(x => !!x)
}

module.exports = { get }
