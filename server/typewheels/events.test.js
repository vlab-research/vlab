const referral =  {
  recipient: { id: '1051551461692797' },
  timestamp: 1542123799219,
  sender: { id: '1800244896727776' },
  referral:
   { ref: 'FOO.rao.hello.ok',
     source: 'SHORTLINK',
     type: 'OPEN_THREAD' } }

// multiple choice response
const multipleChoice = {
  recipient: { id: '1051551461692797' },
  timestamp: 1542116257642,
  sender: { id: '1800244896727776' },
  postback:
   { payload: '{"value":true,"ref":"foo"}',
     title: 'I Accept' } }

// Continue sent by user...
const text = {
  sender: { id: '1800244896727776' },
  recipient: { id: '1051551461692797' },
  timestamp: 1542116363617,
  message: { text: 'foo' } }

// Continue via quick reply...
const qr = {
  sender: { id: '1800244896727776' },
  recipient: { id: '1051551461692797' },
  timestamp: 20,
  message:
   { quick_reply: { payload: 'Continue' },
     text: 'Continue' } }

  // read
const read =  {
  sender: { id: '1800244896727776' },
    recipient: { id: '1051551461692797' },
    timestamp: 15,
    read: {watermark: 10 } }

const delivery = {
  sender: { id: '1800244896727776' },
  recipient: { id: '1051551461692797' },
  timestamp: 16,
  delivery:
   { watermark: 15 }}


  // is echo
const echo = {
  sender: { id: '1051551461692797' },
  recipient: { id: '1800244896727776' },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: '{ "ref": "foo" }',
    text: 'Whatsupp welcome you agree or what?' } }

const statementEcho = {
  sender: { id: '1051551461692797' },
  recipient: { id: '1800244896727776' },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: '{ "ref": "bar", "type": "statement" }',
    text: 'Whatsupp, welcome.' } }

const repeatEcho = {
  sender: { id: '1051551461692797' },
  recipient: { id: '1800244896727776' },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: '{ "ref": "bar", "repeat": "true" }',
    text: 'Whatsupp, welcome.' } }

module.exports = { echo, statementEcho, repeatEcho, delivery, read, qr, text, multipleChoice, referral }
