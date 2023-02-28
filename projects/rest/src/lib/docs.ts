import { Observable, of, switchMap } from "rxjs";
import { TableData, TableQuery, TableDataService, TableQueryWhere, TableFieldValue } from "./table-data-source";

export type DocsQuery = TableQuery & {
  path: string,
  idField: string,
}

export type ArrayUnion = {
  [key: string]: TableFieldValue[]
}

export interface Docs {
  
  valueChanges: {
   <T>(params: DocsQuery)
    : Observable<T[]>
  }

  count: {
    (params: DocsQuery)
    : Observable<number>
  }

  // TODO: status

  create: {
    (params: {
      path: string,
      doc: TableData
    }): Observable<string>
  }

  updateById: {
    (params: {
      path: string,
      partial?: TableData,
      arrayUnion?: ArrayUnion,
    }): Observable<void>
  }

}

export abstract class DocsTableDataService<T extends TableData> implements TableDataService<T> {

  constructor(private params: {
      docs: Docs,
      path: string,
      idField: string,
      where?: Observable<TableQueryWhere | null>
    }
  ){}

  valueChanges(params?: TableQuery): Observable<T[] | null> {
    if (!params) {
      params = {}
    }
    return this.switchWhere(params, null, (params) => this.params.docs.valueChanges<T>(params))
  }

  count(params?: TableQuery): Observable<number> {
    if (!params) {
      params = {}
    }
    return this.switchWhere(params, 0, (params) => this.params.docs.count(params))
  }

  create(params: {
    doc: T
  }) {
    return this.params.docs.create({
      path: this.params.path,
      doc: params.doc,
    })
  }

  updateById(params: {
    id: string,
    partial?: Partial<T>,
    arrayUnion?: ArrayUnion,
  }): Observable<void> {
    return this.params.docs.updateById({
      path: `${this.params.path}/${params.id}`,
      partial: params.partial,
      arrayUnion: params.arrayUnion,
    })
  }

  private switchWhere<S>(params: TableQuery, ifNull: S, fn: (params: DocsQuery) => Observable<S>): Observable<S> {
    if (this.params.where) {
      return this.params.where.pipe(
        switchMap(w => {
          if (!w) {
            return of(ifNull)
          }
          const mergedParams = {...params, where: [...params.where ?? [], ...w]}
          return fn(this.toDocsQuery(mergedParams))
        })
      )
    } else {
      return fn(this.toDocsQuery(params))
    }
  }

  private toDocsQuery(params: TableQuery) {
    return {...params, path: this.params.path, idField: this.params.idField}
  }

}