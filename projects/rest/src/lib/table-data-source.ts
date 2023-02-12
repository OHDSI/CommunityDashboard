import { DataSource } from '@angular/cdk/collections';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { concatMap } from 'rxjs/operators';
import { Observable, merge, of } from 'rxjs';
import { RestDelegate } from './rest-delegate';

export class TableDataSource<T extends {[key: string]: any}> extends DataSource<T> {
  paginator: MatPaginator | undefined;
  sort: MatSort | undefined;

  constructor(
    private rest: RestDelegate<T>,
    private where?: {[key: string]: string | number}
  ) {
    super();
  }

  connect(): Observable<T[]> {
    if (this.paginator && this.sort) {
      return merge(of({}), this.rest.changes, this.paginator.page, this.sort.sortChange)
        .pipe(
          concatMap(() => {
            const skip = this.paginator!.pageIndex * this.paginator!.pageSize;
            const order = (!this.sort || !this.sort.active || this.sort.direction === '') ?
              undefined
              :
              [`${this.sort.active} ${this.sort.direction}`]
            return this.rest.find({
              filter: {skip, limit: this.paginator!.pageSize, order, where: this.where}
            })
          }),
        );
    } else {
      throw Error('Please set the paginator and sort on the data source before connecting.');
    }
  }

  disconnect(): void {}

}
