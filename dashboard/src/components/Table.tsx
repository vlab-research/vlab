import React from 'react';

interface SimpleTableProps<T> {
  data: T[];
}

const SimpleTable = <T extends Record<string, any>>({ data = [] }: SimpleTableProps<T>) => {
  if (!data.length) {
    return <div className="text-gray-500">No data available</div>;
  }

  // Get headers from the first object's keys
  const headers = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200">
        <thead>
          <tr className="bg-gray-100">
            {headers.map((header) => (
              <th 
                key={header} 
                className="px-6 py-3 text-left text-sm font-semibold text-gray-600"
              >
                {/* Convert header from camelCase/snake_case to Title Case */}
                {header
                  .replace(/([A-Z])/g, ' $1')
                  .replace(/_/g, ' ')
                  .replace(/^./, str => str.toUpperCase())}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-t border-gray-200">
              {headers.map((header, colIndex) => (
                <td 
                  key={`${rowIndex}-${colIndex}`} 
                  className="px-6 py-4 text-sm text-gray-800"
                >
                  {row[header]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default SimpleTable;
