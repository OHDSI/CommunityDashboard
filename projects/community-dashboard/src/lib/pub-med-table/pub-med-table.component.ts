import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, ViewChild } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSourceOld } from '../table-data-source-old';
import { Publication, PublicationsService } from './publications.service';

@Component({
  selector: 'app-pub-med-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    CommonModule
  ],
  templateUrl: './pub-med-table.component.html',
  styleUrls: ['./pub-med-table.component.css']
})
export class PubMedTableComponent implements AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<Publication>;
  dataSource: TableDataSourceOld<Publication>;

  @Input()
  displayedColumns!: string[]

  constructor(
    public publicationsService: PublicationsService,
  ) {
    this.dataSource = new TableDataSourceOld(publicationsService);
  }

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }
}
