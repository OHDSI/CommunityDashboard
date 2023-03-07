import { HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, concat, concatAll, concatMap, delay, from, map, Observable, of, reduce, Subject, takeLast, tap } from 'rxjs';
import { Change, Filter, FilterColumn, Id, Rest, Where } from './rest';

// Utilities for indexing in memory data

export function index(a: any[]) {
  return a.reduce(([acc, i], v) => {acc[v.id || `i${i.toString()}`] = v; return [acc, i+1]}, [{}, 0])[0]
}

export function indexAll(fixtures: {[key: string]: any[]}) {
  const indexed: {[key: string]: {[key: Id]: object}} = {}
  for (const k in fixtures) {
    indexed[k] = index(fixtures[k])
  }
  return indexed
}

export function records(a: {[key: string]: {[key: string]: any}}) {
  const records: {[key: Id]: {[key: string]: any}} = {}
  for (const [c, rs] of Object.entries(a)) {
    for (const [k, r] of Object.entries(rs)) {
      if (!(k in records)) {
        const n: {[key: string]: any} = {
          id: k
        }
        records[k] = n
      }
      records[k][c] = r
    }
  }
  return records
}

export class RestMemory implements Rest {

  changes = new Subject<Change>()
  status = new BehaviorSubject<HttpErrorResponse | null>(null)
  tables: Observable<{[key: string]: {[key: Id]: object}}>

  constructor(
    tables: {[key: string]: {[key: Id]: object}} | Observable<{[key: string]: {[key: Id]: object}}>
  ) {
    if (tables instanceof Observable) {
      this.tables = tables
    } else {
      this.tables = of(tables)
    }
  }

  _getTableOrThrow(tables: {[key: string]: {[key: Id]: object}}, path: string, scope?: string) {
    if (!scope) {
      scope = ''
    }
    const t =  tables[`${scope}/${path}`]
    if (!t) {
      throw new Error(`Expected memory table to be defined for path ${path}.`)
    }
    return t
  }

  create<T extends object>(params: {
    path: string,
    body: Omit<T, 'id'>
  }): Observable<T> {

    return this.tables.pipe(
      map(ts => this._getTableOrThrow(ts, params.path)),
      map(t => {
        const id = Object.keys(t).length.toString()
        const n = {...params.body, id} as T
        t[id] = n
        return n
      }),
      delay(2000),
      tap(_ => this.changes.next({}))
    )
  }

  replaceById<T>(params: {
    path: string,
    id: Id,
    body: Omit<T, 'id'> | T
  }): Observable<T> {
    return this.tables.pipe(
      map(ts => this._getTableOrThrow(ts, params.path)),
      map(table => {
        const n = {id: params.id, ...params.body}
        table[params.id] = n; return n as T
      }),
      delay(2000),
      tap(_ => this.changes.next({}))
    )
  }

  updateById<T>(params: {
    path: string,
    id: Id,
    body: Partial<Omit<T, 'id'>> | T
  }): Observable<T> {
    return this.tables.pipe(
      map(ts => this._getTableOrThrow(ts, params.path)),
      map(table => {
        const a = table[params.id] as {[key: Id]: object}
        for (const [k, v] of Object.entries(params.body as object)) {
          a[k] = v
        }
        return a as T
      }),
      delay(2000),
      tap(_ => this.changes.next({}))
    )
  }

  find<T extends {[key: string]: any}>(params: {
    host: string,
    path: string,
    scope?: string,
    converter?: any,
    filter?: Filter,
  }): Observable<T[]> {
    return this.tables.pipe(
      map(ts => this._getTableOrThrow(ts, params.path, params.scope)),
      map(table => {
        const d = Object.values({...table}) as T[]
        const f = params.filter ? filterMemory(d, params.filter) : d
        return f
      }),
      delay(500)
    )
  }

  findById<T>(params: {
    host: string,
    path: string,
    id: Id,
    scope?: string,
  }): Observable<T> {
    return this.tables.pipe(
      map(ts => this._getTableOrThrow(ts, params.path, params.scope)),
      map(table => {
        if (!(params.id in table)) {
          throw new HttpErrorResponse({status: 404})
        }
        return table[params.id] as T
      }),
      delay(500)
    )
  }

  count(params: {
    path: string
    filter?: {
      where?: { [key: string]: any },
    }
  }): Observable<number> {
    return this.tables.pipe(
      map(ts => this._getTableOrThrow(ts, params.path)),
      map(table => {
        let d = Object.values({...table}) as any[]
        if (params.filter?.where) {
          d = filterMemory(d, {where: params.filter.where})
        }
        return d.length
      }),
      delay(500)
    )
  }
}

export const filterMemory = <T extends {[key: string]: any}>(
  d: T[],
  filter: Filter
) => {
  let f = [...d]
  if (filter.where) {
    if (filter.where.or) {
      f =_filterOr(f, filter.where.or)
    } else {
      f = _filterAnd(f, filter.where)
    }
  }
  if (filter.order) {
    order(f, filter.order)
  }
  if (filter.skip !== undefined || filter.limit !== undefined) {
    const skip = filter.skip ? filter.skip : 0
    f = f.splice(skip, filter.limit)
  }
  return f
}

const _filterOr = <T extends {[key: string]: any}>(f: T[], a: FilterColumn[]) => {
  return [...f.filter(r => {
    return a.reduce((m, f) => _and(r, f) || m, false)
  })]
}

const _and = <T extends {[key: string]: any}>(r: T, f: FilterColumn) => {
  return Object.entries(f).reduce((m, [fk, fv]) => m && _match(r[fk], fv), true)
}

const _match = (v: any, fv: any) => {
  if (fv.like) {
    return (v as string).toLowerCase().includes(fv.like.toLowerCase())
  }
  return v === fv
}

const _filterAnd = <T extends {[key: string]: any}>(f: T[], a: Where) => {
  for (const [k, v] of Object.entries(a)) {
    f = [...f.filter(r => r[k] === v)]
  }
  return f
}

const order = <T>(data: T[], order: string[]): void => {
  order.reduceRight((_: null | void, o): void => {
    const [key, direction] = o.split(' ')
    data.sort((a: any, b: any) => {
      const isAsc = direction.toLowerCase() === 'asc';
      switch (key) {
        // case 'title': return compare(a.title, b.title, isAsc);
        // case 'id': return compare(+a.id, +b.id, isAsc);
        default: return compare(a[key], b[key], isAsc);
      }
    });
  }, null)
}

const compare = (a: any, b: any, isAsc: boolean): number => {
  return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
}