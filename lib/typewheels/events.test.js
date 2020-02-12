const USER_ID = '1800244896727776'

const referral =  {
  recipient: { id: '1051551461692797' },
  timestamp: 1542123799219,
  sender: { id: USER_ID },
  referral:
   { ref: 'form.FOO.foo.bar',
     source: 'SHORTLINK',
     type: 'OPEN_THREAD' } }

// multiple choice response
const multipleChoice = {
  recipient: { id: '1051551461692797' },
  timestamp: 1542116257642,
  sender: { id: USER_ID },
  postback:
   { payload: {value:true,ref:"foo"},
     title: 'I Accept' } }

const getStarted = {
  recipient: { id: '1051551461692797' },
  timestamp: 1542116257642,
  sender: { id: USER_ID },
  postback: {
    payload: "get_started",
    referral: {
      ref: "form.FOO",
      source: "SHORTLINK",
      type: "OPEN_THREAD",
    },
    title: 'Get Started'
  }
}
// Text sent by user...
const text = {
  sender: { id: USER_ID },
  recipient: { id: '1051551461692797' },
  timestamp: 1542116363617,
  message: { text: 'foo' } }


const sticker = {
  sender: { id: USER_ID },
  recipient: { id: '1051551461692797' },
  timestamp: 1542116363617,
  message: { stickerId: 369239263222822, attachments: [{ type: 'image' }]} }

// Continue via quick reply...
const qr = {
  sender: { id: USER_ID },
  recipient: { id: '1051551461692797' },
  timestamp: 20,
  message:
   { quick_reply: { payload: { value:"Continue",ref:"foo" }}}}

  // read
const read =  {
  sender: { id: USER_ID },
    recipient: { id: '1051551461692797' },
    timestamp: 15,
    read: {watermark: 10 } }

const delivery = {
  sender: { id: USER_ID },
  recipient: { id: '1051551461692797' },
  timestamp: 16,
  delivery:
   { watermark: 15 }}

  // is echo
const echo = {
  sender: { id: '1051551461692797' },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: { "ref": "foo" },
    text: 'Whatsupp welcome you agree or what?' } }

const statementEcho = {
  sender: { id: '1051551461692797' },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: { "ref": "bar", "type": "statement" },
    text: 'Whatsupp, welcome.' } }

const tyEcho = {
  sender: { id: '1051551461692797' },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: { "ref": "baz", "type": "thankyou_screen" },
    text: 'Thanks' } }


const fakeEcho = {
  sender: { id: '1051551461692797' },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { fake_echo: true,
    is_echo: true,
    metadata: { "ref": "foo", "type": "statement" },
    text: 'Whatsupp, welcome.' } }

const repeatEcho = {
  sender: { id: '1051551461692797' },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: {ref: "bar", repeat: "true" },
    text: 'Whatsupp, welcome.' } }

const syntheticTimeout = {
  source: 'synthetic',
  sender: { id: '' },
  recipient: { id: ''},
  timestamp: 15,
  message: {}
}

const syntheticWatchedVideo = {
  source: 'synthetic',
  sender: { id: '' },
  recipient: { id: ''},
  timestamp: 15,
  message: {}
}

module.exports = { getStarted, echo, fakeEcho, tyEcho, statementEcho, repeatEcho, delivery, read, qr, text, sticker, multipleChoice, referral, USER_ID }
