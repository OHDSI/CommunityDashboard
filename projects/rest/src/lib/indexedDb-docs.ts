import { delay, first, map, Observable, of, Subject, tap } from "rxjs";
import { ArrayUnion, Docs, DocsQuery } from "./docs";
import { OrderBy, TableData, TableQuery, TableQueryWhere, TableFieldPrimitive } from "./table-data-source";
import { combineLatest } from "rxjs/internal/observable/combineLatest";
import { BehaviorSubject } from "rxjs/internal/BehaviorSubject";

interface JsonExport {
  [key:string]: { // collection name
    [key: string]: JsonDoc // doc id
  }
}

interface JsonDoc { 
  [key: string]: unknown,
  subCollection?: JsonExport
}

export interface FixtureIndex {
  [key: string]: { // path
    [key: string]: unknown
  }
}

export function parseExport(e: JsonExport, index?: FixtureIndex): FixtureIndex {
  if (!index) {
    index = {}
  }

  return Object.entries(e).reduce((accIndex: FixtureIndex, [collectionNamestring, collection]: [string, {[key: string]: JsonDoc}]) => {
    
    const docs = Object.entries(collection).reduce((accCollection, [id, doc]) => {
      const {subCollection, ...data} = doc
      accCollection[id] = data
      if (subCollection) {
        parseExport(subCollection, accIndex)
      }
      return accCollection
    }, {} as {[key: string]: JsonDoc})
    
    const path: string = `/${collectionNamestring}`
    accIndex[path] = docs
    return accIndex
  }, index)
}

export class IndexedDbDocs implements Docs {

  changes = new BehaviorSubject<any>(null)
  tableChanges = combineLatest([
    this.changes,
    this.params.tables,
  ]).pipe(map(([_, ts]) => ts))

  constructor(private params: {
    tables: Observable<{[key: string]: {[key: string]: unknown}}>,
  }) {}

  valueChanges<T extends TableData>(params: DocsQuery): Observable<T[]> {
    return this.tableChanges.pipe(
      map(ts => this._getTableOrThrow(ts, params.path)),
      map(table => {
        const d = Object.values({...table}) as T[]
        const f = this.filterMemory<T>(d, params)
        return f
      }),
    )
  }

  count<T extends TableData>(params: DocsQuery): Observable<number> {
    return this.tableChanges.pipe(
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
    return this.params.tables.pipe(
      first(),
      map(ts => this._getTableOrThrow(ts, params.path)),
      map(t => {
        const id = Object.keys(t).length.toString()
        const n = {...params.doc, id}
        t[id] = n
        return id
      }),
      delay(2000),
      tap(_ => this.changes.next({}))
    )
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
    return this.params.tables.pipe(
      first(),
      map(ts => {
        const [collection, id] = this.parsePath(params.path)
        const t = this._getTableOrThrow(ts, collection)
        const n = {...params.doc, id}
        t[id] = n
      }),
      tap(_ => this.changes.next({}))
    )
  }

  deleteById(params: {
    path: string,
  }): Observable<void> {
    const [collection, id] = this.parsePath(params.path)
    return this.params.tables.pipe(
      first(),
      map(ts => this._getTableOrThrow(ts, collection)),
      map((t) => {
        delete t[id]
      }),
      tap(_ => this.changes.next({}))
    )
  }

  parsePath(path: string): [string, string] {
    const segments = path.split('/')
    const collection = segments.slice(0, segments.length - 1).join('/')
    const id = segments[segments.length - 1]
    return [collection, id]
  }

  _getTableOrThrow(tables: {[key: string]: {[key: string]: unknown}}, path: string, scope?: string) {
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
    if (operator === 'array-contains') {
      return [...f.filter(r => (r[q[0]] as TableFieldPrimitive[]).includes(q[2] as TableFieldPrimitive))]
    }
    if (operator === 'in') {
      return [...f.filter(r => (q[2] as TableFieldPrimitive[]).includes(r[q[0]] as TableFieldPrimitive))]
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