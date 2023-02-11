import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, ViewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSource } from 'rest';
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
export class StudiesTableComponent implements AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<Study>;

  @Input() stage!: string

  dataSource!: TableDataSource<Study>
  count = () => this.studiesService.count({filter: {where: {status: this.stage}}})

  @Input()
  displayedColumns: string[] = ["title", "lastUpdate", "protocol", "results"]

  constructor(
    private studiesService: StudiesService,
  ) {}

  ngAfterViewInit(): void {
    this.dataSource = new TableDataSource(this.studiesService, {status: this.stage})
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }
}
