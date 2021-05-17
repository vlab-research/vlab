const snooze = ms => new Promise(resolve => setTimeout(resolve, ms))

module.exports = { snooze }
