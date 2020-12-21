const { Credential } = require('../../queries');


exports.createCredential = async function (req, res) {
  const { entity, details } = req.body;
  const { email } = req.user;

  try {
    const cred = await Credential.create({entity, details, email});
    return res.status(201).json(cred);
  } catch (e) {
    console.error(e)
    return res.status(500).send(e);
  }
}

exports.getCredentials = async function (req, res) {
  const { email } = req.user;

  try {
    const creds = await Credential.get({email});
    return res.status(200).json(creds);
  } catch (e){
    console.error(e)
    return res.status(500).send(e);
  }
}
