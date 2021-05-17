const user = {
    name : 'Leonardo Di Vittorio',
    first_name : 'Leonardo',
    last_name : 'Di Vittorio'
};

module.exports = {
  getUser: (id) => ({...user, id })
}
