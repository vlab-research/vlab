import { formBuilder, getInitialValue } from './formBuilder';
import TextComponent from '../pages/NewStudyPage/form/inputs/Text';
import SelectComponent from '../pages/NewStudyPage/form/inputs/Select';
import text from '../../mocks/text.json';
import select from '../../mocks/select.json';
import number from '../../mocks/number.json';

describe('formBuilder', () => {
  it('given a field it returns a new object configured for rendering a form', () => {
    const textField = text;

    const expectation = {
      id: 'foo',
      name: 'foo',
      type: 'text',
      component: TextComponent,
      label: 'Foo',
      helper_text: 'foo',
      call_to_action: undefined,
      options: undefined,
      value: '',
    };

    const res = formBuilder(textField);
    expect(res).toStrictEqual(expectation);

    const selectField = select;

    const expectation2 = {
      id: 'bar',
      name: 'bar',
      type: 'select',
      component: SelectComponent,
      label: 'Bar',
      helper_text: undefined,
      call_to_action: undefined,
      options: [
        {
          name: 'foo',
          label: 'Foo',
        },
        {
          name: 'bar',
          label: 'Bar',
        },
        {
          name: 'baz',
          label: 'Baz',
        },
      ],
      value: 'foo',
    };

    const res2 = formBuilder(selectField);
    expect(res2).toStrictEqual(expectation2);
  });
});

describe('getInitialValue', () => {
  it('given a field it returns an initial value based on its type', () => {
    let res = getInitialValue(text);
    expect(res).toStrictEqual('');

    res = getInitialValue(number);
    expect(res).toStrictEqual(0);

    res = getInitialValue(select);
    expect(res).toStrictEqual('foo');
  });
});
