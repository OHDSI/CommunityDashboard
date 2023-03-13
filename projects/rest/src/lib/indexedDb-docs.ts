import { map, Observable, of } from "rxjs";
import { ArrayUnion, Docs, DocsQuery } from "./docs";
import { OrderBy, TableData, TableQuery, TableQueryWhere } from "./table-data-source";

export class IndexedDbDocs implements Docs {

  constructor(private params: {
    tables: Observable<{[key: string]: {[key: string]: object}}>,
  }) {}

  valueChanges<T extends TableData>(params: DocsQuery): Observable<T[]> {
    return this.params.tables.pipe(
      map(ts => this._getTableOrThrow(ts, params.path)),
      map(table => {
        const d = Object.values({...table}) as T[]
        const f = this.filterMemory<T>(d, params)
        return f
      }),
    )
  }

  count<T extends TableData>(params: DocsQuery): Observable<number> {
    return this.params.tables.pipe(
      map(ts => this._getTableOrThrow(ts, params.path)),
      map(table => {
        const d = Object.values({...table}) as T[]
        const f = this.filterMemory<T>(d, params)
        return f.length
      }),
    )
  }

  create(params: {
    path: string,
    doc: TableData
  }): Observable<string> {
    throw new Error('not implemented')
  }

  updateById(params: {
    path: string,
    partial?: TableData,
    arrayUnion?: ArrayUnion,
  }): Observable<void> {
    throw new Error('not implemented')
  }

  replaceById(params: {
    path: string,
    doc: TableData,
  }): Observable<void> {
    throw new Error('not implemented')
  }

  _getTableOrThrow(tables: {[key: string]: {[key: string]: object}}, path: string, scope?: string) {
    if (!scope) {
      scope = ''
    }
    const t =  tables[`${scope}/${path}`]
    if (!t) {
      throw new Error(`Expected memory table to be defined for path ${path}.`)
    }
    return t
  }

  private filterMemory<T extends TableData> (
    d: T[],
    q: DocsQuery
  ) {
    let f = [...d]
    if (q.where) {
      f = this.filterAnd(f, q.where)
    }
    if (q.orderBy) {
      this.order(f, q.orderBy)
    }
    if (q.startAfter) {
      const i = f.findIndex(r => r[q.idField] === q.startAfter![q.idField])
      if (i) {
        f.splice(0, i+1)
      }
    }
    if (q.limit) {
      f.splice(q.limit)
    }
    return f
  }

  private filterAnd<T extends TableData>(f: T[], a: TableQueryWhere[]) {
    for (const q of a) {
      f = this.filter(f, q)
    }
    return f
  }

  private filter<T extends TableData>(f: T[], q: TableQueryWhere): T[] {
    const operator = q[1]
    if (operator === '==') {
      return [...f.filter(r => r[q[0]] === q[2])]
    }
    throw new Error('Operator not implemented for IndexedDb.')
  }

  private order<T>(data: T[], order: OrderBy[]): void {
    order.reduceRight((_: null | void, o): void => {
      const [key, direction] = o
      data.sort((a: any, b: any) => {
        const isAsc = direction.toLowerCase() === 'asc';
        switch (key) {
          // case 'title': return compare(a.title, b.title, isAsc);
          // case 'id': return compare(+a.id, +b.id, isAsc);
          default: return this.compare(a[key], b[key], isAsc);
        }
      });
    }, null)
  }

  private compare(a: any, b: any, isAsc: boolean): number {
    return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
  }

}