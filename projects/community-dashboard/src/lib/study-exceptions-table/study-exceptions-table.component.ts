import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, ViewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSource } from 'rest';
import { EXCEPTIONS, StudyException, StudyExceptionsService } from './study-exceptions.service';

@Component({
  selector: 'app-study-exceptions-table',
  standalone: true,
  imports: [
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    CommonModule
  ],
  templateUrl: './study-exceptions-table.component.html',
  styleUrls: ['./study-exceptions-table.component.css']
})
export class StudyExceptionsTableComponent implements AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<StudyException>;

  EXCEPTIONS = EXCEPTIONS
  dataSource: TableDataSource<StudyException> = new TableDataSource(this.studyExceptionsService)
  count = this.studyExceptionsService.count.bind(this.studyExceptionsService)

  @Input()
  displayedColumns: string[] = ["studyRepo", "exception"]

  constructor(
    private studyExceptionsService: StudyExceptionsService,
  ) {}

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }
}
