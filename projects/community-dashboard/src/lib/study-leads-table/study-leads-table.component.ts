import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, ViewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSource } from 'rest';
import { StudyLead, StudyLeadsService } from './study-leads.service';

@Component({
  selector: 'app-study-leads-table',
  standalone: true,
  imports: [
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    CommonModule
  ],
  templateUrl: './study-leads-table.component.html',
  styleUrls: ['./study-leads-table.component.css']
})
export class StudyLeadsTableComponent implements AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<StudyLead>;

  dataSource: TableDataSource<StudyLead> = new TableDataSource(this.studyLeadsService)
  count = this.studyLeadsService.count.bind(this.studyLeadsService)

  @Input()
  displayedColumns: string[] = ["name", "active", "completed"]

  constructor(
    private studyLeadsService: StudyLeadsService,
  ) {}

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }
}
