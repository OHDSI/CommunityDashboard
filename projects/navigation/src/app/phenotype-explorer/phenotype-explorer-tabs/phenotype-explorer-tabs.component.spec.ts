import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PhenotypeExplorerTabsComponent } from './phenotype-explorer-tabs.component';

describe('PhenotypeExplorerTabsComponent', () => {
  let component: PhenotypeExplorerTabsComponent;
  let fixture: ComponentFixture<PhenotypeExplorerTabsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ PhenotypeExplorerTabsComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PhenotypeExplorerTabsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
