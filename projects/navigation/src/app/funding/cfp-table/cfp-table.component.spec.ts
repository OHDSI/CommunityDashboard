import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CfpTableComponent } from './cfp-table.component';

describe('CfpTableComponent', () => {
  let component: CfpTableComponent;
  let fixture: ComponentFixture<CfpTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ CfpTableComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CfpTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
