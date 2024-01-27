import AddButton from '../../../components/AddButton';
import DeleteButton from '../../../components/DeleteButton';

interface hasName {
  name: string;
}

interface ListProps<T> {
  data: T[];
  setData: (a: T[]) => void;
  initialState: T[];
  Element: any;
  elementName: string;
  elementProps?: object;
}

export const GenericListFactory = <T extends hasName>(): React.FC<ListProps<T>> => ({ data, setData, initialState, Element, elementProps, elementName }: ListProps<T>) => {

  const updateElement = (a: T, index: number): void => {
    const clone = [...data];
    clone[index] = a;
    setData(clone);
  };

  const addItem = (): void => {
    setData([...data, ...initialState]);
  };

  const deleteItem = (i: number): void => {
    const newArr = data.filter((_: T, ii: number) => ii !== i);
    setData(newArr);
  };

  return (
    <div className="mb-8">
      {data.map((d: T, index: number) => {
        return (
          <ul key={index}>
            <Element
              data={d}
              index={index}
              update={updateElement}
              {...elementProps}
            />
            {data.length >= 1 && (
              <div key={`${d.name}-${index}`}>
                <div className="flex flex-row w-4/5 justify-between items-center">
                  <div className="flex w-full h-0.5 mr-4 rounded-md bg-gray-400"></div>
                  <DeleteButton
                    onClick={() => deleteItem(index)}
                  ></DeleteButton>
                </div>
                <div />
              </div>
            )}
          </ul>
        );
      })}
      <AddButton onClick={addItem} label={`Add ${elementName}`} />
    </div>
  )
}
