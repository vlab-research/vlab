const { User } = require('../../queries');

exports.createUser = async (req, res) => {
  try {
    const user = await User.create(req.user)
    res.status(200).json(user)
  } catch (e) {
    res.status(500).send(e)
  }
}
