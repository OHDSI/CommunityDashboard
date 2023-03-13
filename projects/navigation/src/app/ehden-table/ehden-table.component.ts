import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, ViewChild } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSource  } from '@community-dashboard/rest';
import { CourseStat, CourseStatsService } from '../ehden/ehden.service';

@Component({
  selector: 'app-ehden-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    CommonModule
  ],
  templateUrl: './ehden-table.component.html',
  styleUrls: ['./ehden-table.component.css']
})
export class EhdenTableComponent implements AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<CourseStat>;
  dataSource: TableDataSource<CourseStat>;

  @Input()
  displayedColumns!: string[]

  count = this.courseStatsService.count()

  constructor(
    private courseStatsService: CourseStatsService,
  ) {
    this.dataSource = new TableDataSource(courseStatsService);
  }

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }
}
