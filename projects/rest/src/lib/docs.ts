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
   <T extends TableData>(params: DocsQuery)
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

  replaceById: {
    (params: {
      path: string,
      doc: TableData,
    }): Observable<void>
  }

  deleteById: {
    (params: {
      path: string,
    }): Observable<void>
  }

}

/**
 * Delegates the implementation of the TableDataService
 * to a Docs for a particular TableData.
 * 
 * Optionally, constrain all TableData with a where defined
 * during construction.
 */
export abstract class DocsTableDataService<T extends TableData> implements TableDataService<T> {

  constructor(private params: {
      docs: Docs,
      path: string,
      idField: string,
      where?: Observable<TableQueryWhere[] | null>
    }
  ){}

  valueChanges(params?: TableQuery): Observable<T[] | null> {
    return this.switchWhere(null, (params) => this.params.docs.valueChanges<T>(params), params)
  }

  count(params?: TableQuery): Observable<number> {
    return this.switchWhere(0, (params) => this.params.docs.count(params), params)
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

  replaceById(params: {
    id: string,
    doc: T,
  }): Observable<void> {
    return this.params.docs.replaceById({
      path: `${this.params.path}/${params.id}`,
      doc: params.doc,
    })
  }

  deleteById(params: {
    id: string
  }): Observable<void> {
    return this.params.docs.deleteById({
      path: `${this.params.path}/${params.id}`
    })
  }

  /**
   * 
   * @returns the "inner" observable from fn using the latest this.params.where 
   *          "outer" observable, or ifNull when this.params.where emits null.
   */
  private switchWhere<S>(ifNull: S, fn: (params: DocsQuery) => Observable<S>, params?: TableQuery): Observable<S> {
    // Originally, I was merging the where queries. But, this didn't make sense for most use
    // cases. Now if params.where is passed it just overrides this.params.where.
    if (params?.where || !this.params.where) {
      return fn(this.toDocsQuery({...params}))
    } else {
      return this.params.where.pipe(
        switchMap(w => {
          if (!w) {
            return of(ifNull)
          }
          // const mergedParams = {...params, where: [...params.where ?? [], ...w]}
          const mergedParams = {...params, where: w}
          return fn(this.toDocsQuery(mergedParams))
        })
      )
    }
  }

  private toDocsQuery(params: TableQuery) {
    return {...params, path: this.params.path, idField: this.params.idField}
  }

}