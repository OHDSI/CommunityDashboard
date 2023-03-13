import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, ViewChild } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSource } from '@community-dashboard/rest';
import { Publication, PubmedService } from '../publications/pubmed.service';

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
  dataSource: TableDataSource<Publication>;

  count = this.pubmedService.count()

  @Input()
  displayedColumns!: string[]

  constructor(
    private pubmedService: PubmedService,
  ) {
    this.dataSource = new TableDataSource(pubmedService);
  }

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }
}
