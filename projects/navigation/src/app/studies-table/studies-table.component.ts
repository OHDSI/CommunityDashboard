import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, OnDestroy, ViewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSource  } from '@community-dashboard/rest';
import { Observable, of, Subscription } from 'rxjs';
import { StudiesService, Study } from './studies.service';

@Component({
  selector: 'app-studies-table',
  standalone: true,
  imports: [
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    CommonModule
  ],
  templateUrl: './studies-table.component.html',
  styleUrls: ['./studies-table.component.css']
})
export class StudiesTableComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<Study>;

  @Input() stage!: string

  dataSource!: TableDataSource<Study>
  count?: Observable<number | null>

  @Input()
  displayedColumns: string[] = ["title", "daysAtStage", "lastUpdate", "protocol", "results"]

  constructor(
    private studiesService: StudiesService,
  ) {}

  countSubscription?: Subscription

  ngOnDestroy(): void {
    this.countSubscription?.unsubscribe()
  }

  ngAfterViewInit(): void {
    setTimeout(() => this.count = this.studiesService.count({where: [['status', '==', this.stage]]}))
    this.dataSource = new TableDataSource(this.studiesService, of([['status', '==', this.stage]]))
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }
}
