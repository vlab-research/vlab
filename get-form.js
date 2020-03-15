require('dotenv').config()

const {getForm} = require('./lib/typewheels/typeform')
const fs = require('fs')

const args = process.argv.slice(2)

async function foo () {
  for (let FORM of args) {
    const forms = await getForm(FORM)
    const form = forms[0]
    fs.writeFileSync(`../facebot/testrunner/forms/${FORM}.json`, JSON.stringify(form, null, 2))
  }
}

foo()
