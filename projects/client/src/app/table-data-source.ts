import { DataSource } from '@angular/cdk/collections';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { concatMap } from 'rxjs/operators';
import { Observable, merge, of, Subject } from 'rxjs';

export interface Change {}

interface DataService<T> {

  find: (params?: {
    id?: number,
    filter?: {
      skip?: number,
      limit?: number,
      order?: string[],
    }
  }) => Observable<T[]>

  changes: Subject<Change>
}

export class TableDataSource<T> extends DataSource<T> {
  paginator: MatPaginator | undefined;
  sort: MatSort | undefined;

  constructor(
    private dataService: DataService<T>,
  ) {
    super();
  }

  connect(): Observable<T[]> {
    if (this.paginator && this.sort) {
      return merge(of({}), this.dataService.changes, this.paginator.page, this.sort.sortChange)
        .pipe(
          concatMap(() => {
            const skip = this.paginator!.pageIndex * this.paginator!.pageSize;
            const order = (!this.sort || !this.sort.active || this.sort.direction === '') ?
              undefined
              :
              [`${this.sort.active} ${this.sort.direction}`]
            return this.dataService.find({
              filter: {skip, limit: this.paginator!.pageSize, order}
            })
          }),
        );
    } else {
      throw Error('Please set the paginator and sort on the data source before connecting.');
    }
  }

  disconnect(): void {}

}
