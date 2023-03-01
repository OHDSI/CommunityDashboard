import { Observable } from "rxjs";
import { ArrayUnion, Docs } from "./docs";
import { TableData, TableQuery } from "./table-data-source";

export class IndexedDbDocs implements Docs {

  constructor(
  ) {}

  valueChanges<T>(params: TableQuery): Observable<T[]> {
    throw new Error('not implemented')
  }

  count(params: TableQuery): Observable<number> {
    throw new Error('not implemented')
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

}