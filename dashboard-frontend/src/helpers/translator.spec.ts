import { translator } from './translator';
import textField from '../../mocks/text.json';
import selectField from '../../mocks/select.json';
import TextInput from '../pages/NewStudyPage/TextInput';
import SelectInput from '../pages/NewStudyPage/Select';

describe('translator', () => {
  it('takes an object and returns a new object configured for creating a form', () => {
    const expectation = {
      id: 'foo_bar',
      name: 'foo_bar',
      type: 'text',
      component: TextInput,
      label: 'Foo',
      helpertext: 'foo',
      options: undefined,
    };

    const res = translator(textField);
    expect(res).toStrictEqual(expectation);

    const expectation2 = {
      id: 'foo_bar',
      name: 'foo_bar',
      type: 'select',
      component: SelectInput,
      label: 'Foo',
      helpertext: undefined,
      options: [
        {
          name: 'foo',
        },
        {
          name: 'bar',
        },
        {
          name: 'baz',
        },
      ],
    };

    const res2 = translator(selectField);
    expect(res2).toStrictEqual(expectation2);
  });
});
