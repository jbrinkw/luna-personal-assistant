import React, { useEffect, useState, useMemo } from 'react';
import { useTable } from 'react-table';

function EditableTable({ columns, data, onSave }) {
  const [tableData, setTableData] = useState(data);

  useEffect(() => setTableData(data), [data]);

  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } = useTable({ columns, data: tableData });

  const handleChange = (rowIndex, columnId, value) => {
    setTableData(old => old.map((row, index) => {
      if (index === rowIndex) {
        return { ...row, [columnId]: value };
      }
      return row;
    }));
  };

  return (
    <table {...getTableProps()} style={{ border: '1px solid black' }}>
      <thead>
        {headerGroups.map(headerGroup => (
          <tr {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map(column => (
              <th {...column.getHeaderProps()} style={{ padding: '4px', borderBottom: '1px solid gray' }}>{column.render('Header')}</th>
            ))}
            <th>Save</th>
          </tr>
        ))}
      </thead>
      <tbody {...getTableBodyProps()}>
        {rows.map(row => {
          prepareRow(row);
          return (
            <tr {...row.getRowProps()}>
              {row.cells.map(cell => (
                <td {...cell.getCellProps()} style={{ padding: '4px' }}>
                  <input value={cell.value ?? ''} onChange={e => handleChange(row.index, cell.column.id, e.target.value)} />
                </td>
              ))}
              <td><button onClick={() => onSave(tableData[row.index])}>Save</button></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default function App() {
  const [tables, setTables] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rows, setRows] = useState([]);
  const [columns, setColumns] = useState([]);
  const [pk, setPk] = useState('id');

  useEffect(() => {
    fetch('/api/tables').then(r => r.json()).then(setTables);
  }, []);

  const loadTable = (name) => {
    setSelected(name);
    fetch(`/api/tables/${name}`).then(r => r.json()).then(setRows);
    fetch(`/api/tables/${name}/info`).then(r => r.json()).then(info => {
      setColumns(info.columns.map(c => ({ Header: c, accessor: c })));
      setPk(info.primaryKey || 'id');
    });
  };

  const saveRow = (row) => {
    const idVal = row[pk];
    fetch(`/api/tables/${selected}/${idVal}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(row)
    }).then(() => loadTable(selected));
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ width: '200px', borderRight: '1px solid gray', padding: '8px' }}>
        <h3>Tables</h3>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {tables.map(t => (
            <li key={t}><button style={{ width: '100%' }} onClick={() => loadTable(t)}>{t}</button></li>
          ))}
        </ul>
      </div>
      <div style={{ flex: 1, padding: '8px' }}>
        {selected && <h2>{selected}</h2>}
        {selected && rows.length > 0 && <EditableTable columns={columns} data={rows} onSave={saveRow} />}
      </div>
    </div>
  );
}
