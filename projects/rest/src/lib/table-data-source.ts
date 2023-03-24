import { DataSource } from '@angular/cdk/collections';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { Observable, combineLatest, switchMap, tap, startWith, map } from 'rxjs';

export interface TableData {[key: string]: TableFieldValue}
export type TableFieldValue = TableFieldPrimitive | TableFieldPrimitive[] | TableData | TableData[] | undefined
export type TableFieldPrimitive = string | number | boolean | null

export interface TableQuery {
  where?: TableQueryWhere[],
  orderBy?: OrderBy[],
  limit?: number,
  startAfter?: TableData
}

export type Operator = '==' | 'in' | 'array-contains'
export type OrderBy = [string, 'asc' | 'desc' | '']
export type TableQueryWhere = [string, Operator, TableFieldPrimitive | TableFieldPrimitive[]]
export type TableQueryWhereArray = TableQueryWhere[]

export interface TableDataService<T extends TableData> {

  valueChanges: {
    (params?: TableQuery)
    : Observable<T[] | null>
  }

  count: {
    (params?: TableQuery)
    : Observable<number>
  }
}

export class TableDataSource<T extends TableData> extends DataSource<T> {
  paginator: MatPaginator | undefined
  sort: MatSort | undefined
  lastRow: {[key: number]: T} = {}
  pageSize?: number

  constructor(
    private service: TableDataService<T>,
    private where?: Observable<TableQueryWhere[]>,
  ) {
    super();
  }

  connect(): Observable<T[]> {
    if (this.paginator && this.sort) {
      const whereChanges = []
      if (this.where) {
        whereChanges.push(this.where.pipe(
          tap(_ => {
            this.lastRow = {}
            this.paginator!.firstPage()
          })
        ))
      }
      return combineLatest([
        this.paginator.page.pipe(
          startWith(null),
          tap(page => {
            if (this.pageSize !== undefined && page?.pageSize !== this.pageSize) {
              this.lastRow = {}
              this.paginator!.firstPage()
            }
            this.pageSize = page?.pageSize
          })
        ),
        this.sort.sortChange.pipe(
          startWith(this.sort),
          tap(_ => {
            this.lastRow = {}
            this.paginator!.firstPage()
          })
        ),
        ...whereChanges
      ]).pipe(
        switchMap(([page, sort, where]) => {
          const orderBy: {orderBy?: TableQuery['orderBy']} = {}
          if (sort.active) {
            orderBy!.orderBy = [[sort.active, sort.direction]]
          }
          return this.service.valueChanges({
            where,
            ...orderBy,
            limit: this.paginator!.pageSize,
            startAfter: this.lastRow[page?.pageIndex ?? 0]
          }).pipe(
            map(p => p ?? []),
            tap(p => this.lastRow[this.paginator!.pageIndex + 1] = p[p.length - 1]),
          )
        })
      )
    } else {
      throw Error('Please set the paginator and sort on the data source before connecting.');
    }
  }

  disconnect(): void {}

}
