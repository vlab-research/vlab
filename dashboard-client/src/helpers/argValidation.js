function isRequired(arg) {
  throw new TypeError(`The ${arg} argument is required!`);
}

export default { isRequired };
