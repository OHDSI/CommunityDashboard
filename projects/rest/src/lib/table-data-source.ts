import { DataSource } from '@angular/cdk/collections';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { concatMap } from 'rxjs/operators';
import { Observable, merge, of } from 'rxjs';
import { RestDelegate } from './rest-delegate';
import { Filter, Where } from './rest';

export class TableDataSource<T extends {[key: string]: any}> extends DataSource<T> {
  paginator: MatPaginator | undefined;
  sort: MatSort | undefined;

  constructor(
    private rest: RestDelegate<T>,
    private where?: Where,
    private filter?: Observable<Filter | {}>,
  ) {
    super();
  }

  connect(): Observable<T[]> {
    if (this.paginator && this.sort) {
      const events = [
        of({}), this.rest.changes, this.paginator.page, this.sort.sortChange,
        ...this.filter ? [this.filter] : []
      ]
      return merge(...events)
        .pipe(
          concatMap((f) => this.find(f)),
        );
    } else {
      throw Error('Please set the paginator and sort on the data source before connecting.');
    }
  }

  find(f: any) {
    if ('where' in f) {
      this.where = f.where
    } else {
      this.where = undefined
    }
    const skip = this.paginator!.pageIndex * this.paginator!.pageSize;
    const order = (!this.sort || !this.sort.active || this.sort.direction === '') ?
      undefined
      :
      [`${this.sort.active} ${this.sort.direction}`]
    return this.rest.find({
      filter: {skip, limit: this.paginator!.pageSize, order, where: this.where}
    })
  }

  disconnect(): void {}

}
