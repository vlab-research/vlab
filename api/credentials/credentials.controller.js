const { Credential } = require('../../queries');

// TODO: create unified error handler to clean this up!
// and make useful error codes

exports.createCredential = async function (req, res) {
  const { email } = req.user;

  try {
    const cred = await Credential.create({...req.body, email});
    return res.status(201).json(cred);
  } catch (e) {
    console.error(e)

    if (e.code && e.code === '23505') {
      return res.status(400).json(e);
    }

    if (e.code) {
      return res.status(500).json(e);
    }

    return res.status(500).send(e);
  }
}


exports.updateCredential = async function (req, res) {
  const { email } = req.user;

  try {
    const cred = await Credential.update({...req.body, email});
    if (!cred) {
      return res.status(404).json({'error': `Could not find credentials to match: ${JSON.stringify(req.body)}`})
    }
    return res.status(200).json(cred);
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
